#!/usr/bin/env python3
"""
clay_cm_ck.py: the clay of the two warm-modern corridor stills of the guided route, CM and CK (render-agent, 2026-11-27). 0 var2 tokens.
Spec: docs/proposals/wm-transitions-house-2026-11-26.md, "מסדרון במודרני חם (FB21)" sections 1-3 (the designer's CB is named CK).

The scene is assets/blockout/house/framing_wm_hall_2026_11_18.py exactly (imported, not edited; it imports framing_wm_door_final.py and the
whole house), in HC's state (the corridor portal lined in walnut flush with the plaster, the Nordic casings hidden, the bath window out of
the hall corner and its two plaster patches in), plus, for these two stills only:
  a. every corridor door opening lined in walnut on its reveals (FB21 table 1: "ספים מצופי אגוז"): the jamb and head returns of the boy,
     girl, bath and master openings take the walnut material (#6B4A33, as the portal); the laundry stays plaster (ARR-L1, out of both frames);
  b. the four leaves in the wall colour (FB21 table 1). They already stand on the FB21 hinges, open 90 deg into the rooms: master
     leaf_corridor_master_m1 on X 2.90 (G-M1), boy on Y 13.53, girl on Y 17.16, bath on Y 13.39 (listed in clay-meta.json);
  c. the two cameras, 24 mm, level, shift 0.50 / 0.50 on the 16:9 canvas 2720 x 1530 (HT2's):
       CM (2.45, 14.40, 1.20) yaw 180 (toward the bedroom),  CK (2.45, 14.20, 1.20) yaw 0 (toward the hall).
The front door leaf is closed (out of both frames). Lighting, exposure (0.75), samples and passes as framing_wm_hall_2026_11_18.py.

  python3 clay_cm_ck.py --find                 # what stands at the corridor openings
  python3 clay_cm_ck.py --frames CK,CM [--res 1360 --samples 4 --out DIR]
"""
import argparse
import json
import math
import os
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/user/homedesign-app"
BLK = os.path.join(REPO, "assets/blockout/house")
SCR = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/clay"
os.environ.setdefault("WM_HALL_SCRATCH", SCR)
sys.path.insert(0, BLK)
_MY_ARGV = sys.argv[1:]
sys.argv = [sys.argv[0]]

import framing_wm_hall_2026_11_18 as H  # noqa: E402  (not edited)

import bpy  # noqa: E402
import numpy as np  # noqa: E402

FF, D, E, W4, fr = H.FF, H.D, H.E, H.W4, H.fr
OUT = os.path.join(os.path.dirname(HERE), "clay")
CAMS = dict(CM=dict(loc=[2.45, 14.40, 1.20], yaw=180.0), CK=dict(loc=[2.45, 14.20, 1.20], yaw=0.0))
OPENINGS = dict(boy=dict(x=(1.50, 1.75), y=(12.55, 13.62)), girl=dict(x=(1.50, 1.75), y=(16.18, 17.25)),
                bath=dict(x=(3.05, 3.30), y=(12.30, 13.48)), master=dict(x=(1.92, 2.98), y=(17.46, 17.71)),
                laundry=dict(x=(3.05, 3.30), y=(14.22, 15.18)))


def frames():
    return {k: dict(loc=v["loc"], yaw=v["yaw"], u0=0.50, v0=0.50, leaf="closed", canvas="reg", s=None) for k, v in CAMS.items()}


def inside(ob, box, zmin=-0.01):
    lo, hi = H.wbb(ob)
    return lo[0] >= box["x"][0] - 1e-3 and hi[0] <= box["x"][1] + 1e-3 and lo[1] >= box["y"][0] - 1e-3 and hi[1] <= box["y"][1] + 1e-3 and lo[2] >= zmin


def listing():
    out = {}
    for k, b in OPENINGS.items():
        rows = []
        for ob in bpy.data.objects:
            if ob.type == "MESH" and inside(ob, b):
                lo, hi = H.wbb(ob)
                rows.append(dict(name=ob.name, pidx=int(ob.pass_index), hide=bool(ob.hide_render), lo=[round(v, 3) for v in lo],
                                 hi=[round(v, 3) for v in hi], mat=[m.name for m in ob.data.materials if m]))
        out[k] = rows
    lf = bpy.data.objects.get("leaf_corridor_master")
    out["leaf_corridor_master"] = None if lf is None else [[round(v, 3) for v in H.wbb(lf)[0]], [round(v, 3) for v in H.wbb(lf)[1]]]
    return out


LININGS = dict(  # the reveals of the four open doors (house-plan openings; the openings are plain holes in the wall boxes)
    boy=dict(plane="x", w=(1.55, 1.70), o=(12.63, 13.53)), girl=dict(plane="x", w=(1.55, 1.70), o=(16.26, 17.16)),
    bath=dict(plane="x", w=(3.10, 3.25), o=(12.39, 13.39)), master=dict(plane="y", w=(17.51, 17.66), o=(2.00, 2.90)))
HEAD, T = 2.40, 0.01
PX_WALNUT = 742
LEAVES = ("leaf_corridor_boy", "leaf_corridor_girl", "leaf_corridor_bath", "leaf_corridor_master_m1")


def corridor_wm():
    """a. walnut linings (1 cm boxes on the two jambs and the head of each open corridor door, as framing_wm_kids / _master K-5);
    b. the four leaves in the wall colour (FB21: "חלקות, בגוון הקיר"), checked on their FB21 hinges. Returns notes."""
    walnut = fr.mat_cache("walnut_wm", "#6B4A33", 0.85)
    wall = FF.M["wall"]
    notes = []
    for k, L in LININGS.items():
        (w0, w1), (o0, o1) = L["w"], L["o"]
        if L["plane"] == "x":
            bxs = [(w0, w1, o0, o0 + T, 0.0, HEAD), (w0, w1, o1 - T, o1, 0.0, HEAD), (w0, w1, o0, o1, HEAD - T, HEAD)]
        else:
            bxs = [(o0, o0 + T, w0, w1, 0.0, HEAD), (o1 - T, o1, w0, w1, 0.0, HEAD), (o0, o1, w0, w1, HEAD - T, HEAD)]
        for j, b in enumerate(bxs):
            FF.bx(f"corr_wm_lining_{k}_{'abh'[j]}", *b, walnut, PX_WALNUT, group="framing")
        notes.append(f"{k}: walnut linings 1 cm on both jambs and the head ({L['plane']}-wall {w0}-{w1}, opening {o0}-{o1}, head {HEAD})")
    for n in LEAVES:
        lf = bpy.data.objects.get(n)
        if lf is None:
            notes.append(f"{n}: not in the scene")
            continue
        lf.data = lf.data.copy()
        lf.data.materials.clear()
        lf.data.materials.append(wall)
        lo, hi = H.wbb(lf)
        notes.append(f"{n}: wall colour; X {lo[0]:.2f}-{hi[0]:.2f}, Y {lo[1]:.2f}-{hi[1]:.2f}, Z {lo[2]:.2f}-{hi[2]:.2f}")
    bpy.context.view_layer.update()
    return notes


def args(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--find", action="store_true")
    ap.add_argument("--frames", default="CK,CM")
    ap.add_argument("--res", type=int, default=None)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--out", default=OUT)
    return ap.parse_args(argv)


def main(argv):
    a = args(argv)
    fa = FF.args([])
    fa.res = a.res or D.REG_CANVAS[0]
    os.makedirs(SCR, exist_ok=True)
    W4.r4.EXR_DIR = os.path.join(SCR, "exr")
    t0 = time.time()
    S, R, cfg, notes = FF.build(fa)
    E.IDS.update(H.NEW_IDS)
    D.IDS.update(H.NEW_IDS)
    E.PALETTE.update(H.NEW_PAL)
    E.ALLOWED.update(H.NEW_IDS)
    bo, bn = H.bench()
    co, cn = H.console()
    dark = [o for o in bpy.data.objects if o.type == "MESH" and (o.name.startswith("W-bath_") or o.name == "fluted_glass2")]
    wall = FF.M["wall"]
    patches = [FF.bx("hall_patch_bathwin_a", 3.60, 3.66, 9.60, 9.80, 0.975, 2.15, wall, 100),
               FF.bx("hall_patch_bathwin_b", 3.45, 3.60, 9.80, 9.95, 0.975, 2.15, wall, 100)]
    portal_old, portal_new = H.portal_wm()
    for o in dark + portal_old:                      # HC's state, for both stills
        o.hide_render = True
    for o in patches + portal_new:
        o.hide_render = False
    if a.find:
        print(json.dumps(listing(), indent=1))
        return
    cnotes = corridor_wm()
    print("\n".join(cnotes), flush=True)
    IM = D.index_map_door()
    E.classify = H.classify
    E.edges_of = FF.edges_final
    F = frames()
    os.makedirs(a.out, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="wm-corr-", dir=SCR)
    cam = S["cam"]
    from PIL import Image
    recs = {}
    for fid in a.frames.split(","):
        f = F[fid]
        t1 = time.time()
        D.set_leaf(f["leaf"])
        cv = D.set_view(cam, f, a.res or D.REG_CANVAS[0])
        png = os.path.join(a.out, fid + ".png")
        depth, idx, normal = D.geometry_pass(tmp, cv["W"], cv["H"])
        FF.render_beauty(png, os.path.join(tmp, "p"), cv["W"], cv["H"], a.samples, 0.30, fa.door_exposure, keep_exr=None)
        for nm in ("g", fid):
            q = os.path.join(W4.r4.EXR_DIR, nm + ".exr")
            if os.path.exists(q):
                os.remove(q)
        Image.open(png).save(png, optimize=True)
        rec = dict(frame=fid, camera=dict(loc=f["loc"], yaw=f["yaw"], lens=24, u0=f["u0"], v0=f["v0"]), leaf=f["leaf"], canvas=cv,
                   samples=a.samples, exposure=fa.door_exposure)
        rec.update(E.save_passes(fid, png, depth, idx, normal, f, cv, IM, a.out))
        rec["runtime_s"] = round(time.time() - t1)
        recs[fid] = rec
        print("FRAME", fid, rec["runtime_s"], "s", flush=True)
    meta = dict(stage="warm-modern corridor clay for the guided route (FB21): CM and CK, render-agent 2026-11-27; clay_cm_ck.py on "
                      "framing_wm_hall_2026_11_18.py (not edited); 0 var2 tokens",
                date=time.strftime("%Y-%m-%d"), hc_state="as HC: walnut portal linings flush (Y 9.80-9.95), Nordic casings hidden, bath window "
                "hidden and patched", corridor=cnotes, ids={int(k): v for k, v in E.IDS.items()},
                npz_note="float depth (planar, m), pass index and normals: SCR/passes/<frame>.npz (scratch, not kept)",
                render="as framing_wm_door_final.py: Cycles CPU, OIDN, AgX Medium High Contrast, exposure 0.75", frames=recs,
                build_and_render_s=round(time.time() - t0))
    mp = os.path.join(a.out, "clay-meta.json")
    old = json.load(open(mp)) if os.path.exists(mp) else {}
    fr_old = old.get("frames", {})
    fr_old.update(recs)
    meta["frames"] = fr_old
    json.dump(meta, open(mp, "w"), indent=1, ensure_ascii=False, default=str)
    print("DONE", round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main(_MY_ARGV)
