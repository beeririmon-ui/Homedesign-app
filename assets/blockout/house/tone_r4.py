#!/usr/bin/env python3
"""
Round-4 clay post (render-agent, 2026-11-02; 0 var2 credits). From each frame's composite EXR (framing_r4.py), in this order:
  1. white balance (bath group only: B1, B2, CB-0): per-channel linear gains that make the reference wall patch neutral
     ("re-rendered neutral, no orange", b1-v7 / b2-v7 headers); the lamps keep their warm emission relative to the wall,
  2. exposure: the AgX Medium High Contrast view (as rendered) at the exposure that puts the frame's reference wall at its target
     L (HSL lightness, as framing_r3.patch_L), shared by every frame of one camera point / transition group, so a pan or a pose
     never changes exposure inside a group (transitions plan 1.5),
  3. glass roll-off: a tanh shoulder above 0.88 per channel (max ~0.96), so the brightest glass reads p99 <= 97 (wow pass 4.1),
  4. readings: the reference patches before / after, p99 on the window boxes and on the whole frame, the H0 living / hall ratio.
Exposure is a scene-linear multiply before the view transform, so step 2 equals rendering at that exposure.

  python3 tone_r4.py [--frames M0,D1,...] [--exr DIR] [--out DIR]
Writes framing/round4/<frame>.png, framing/round4/poses/<pose>.png and framing/round4/selfcheck.json (merged with the render selfchecks).
"""
import argparse
import json
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R4 = os.path.join(HERE, "framing", "round4")
SCRATCH = "/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad"
EXR = os.path.join(SCRATCH, "r4-exr")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

# reference patch per exposure group: (frame that sets it, world point (X, Y, Z) or uv, target L, why)
GROUPS = {
    "M0":  dict(frames=["M0", "M0p", "M0x"], ref="M0", pt=("uv", 0.467, 0.385), target=86.5,
                why="m0-v7: the back wall by the corner L 85-90 in the clay (Bible corner point 0.467, 0.385)"),
    "PD":  dict(frames=["D1", "D2", "PD-35"], ref="D1", pt=("xyz", 7.25, 1.00, 2.40), target=86.5,
                why="d1-v7: kitchen wall L 85-90; D2 (left upstand) and PD-35 share the exposure (one point, the P-D pan)"),
    "H0":  dict(frames=["H0", "H0x", "H0e"], ref="H0", pt="living_back_wall_through_door", target=89.0, clamp=False,
                why="h0-v7: the living back wall seen through the door L 88-90, the hall about 2/3 stop under it (living boost in the render)"),
    "C0":  dict(frames=["C0", "S1prime", "R2m"], ref="C0", pt=("xyz", 1.70, 15.0, 1.95), target=87.1, clamp=False,
                why="c0-v7: corridor walls as they are (round 3 gallery wall L 87.1); the vista lifted by the living boost"),
    "MB0": dict(frames=["MB0", "MB-in"], ref="MB0", pt=("xyz", -0.70, 17.66, 1.95), target=86.5,
                why="mb0-v7: the bed wall L 85-90 (round 3 read 78 at this point, hero_wall_mid)"),
    "Kb":  dict(frames=["K-boy", "K-boy-0"], ref="K-boy", pt=("xyz", -1.50, 10.25, 1.95), target=86.5,
                why="k-boy-v7: the white wall over the band by the window L 85-90"),
    "Kg":  dict(frames=["K-girl", "K-girl-0"], ref="K-girl", pt=("xyz", -1.50, 13.88, 1.95), target=86.5,
                why="k-girl-v7: the white wall over the band by the window L 85-90"),
    "CB":  dict(frames=["B1", "B2", "CB-0"], ref="B1", pt=("xyz", 4.55, 9.95, 2.00), target=87.0, wb=True,
                why="b1-v7: the wall beside the window L 86-90, neutral; B2 and CB-0 share exposure and balance (one point, the P-B pan)"),
    "W0":  dict(frames=["W0", "W0-in"], ref="W0", pt=("xyz", -0.825, 6.35, 2.10), target=86.5,
                why="w0-v7: the desk wall L 85-90 (round 3 read 76 across it; this is its hero_wall_mid point above the shelf)"),
}
SHOULDER_K, SHOULDER_M = 0.88, 0.965
WB_STRENGTH = float(os.environ.get("R4_WB_STRENGTH", "0.8"))
EXP_CLAMP = (0.85, 1.85)          # "about +1 stop": round 3 rendered at +0.35; the trim stays within +0.5 .. +1.5 stops of it


def project(C, X, Y, Z):
    yaw = math.radians(C["yaw"])
    cx, cy, cz = C["loc"]
    d = -math.sin(yaw) * (X - cx) - math.cos(yaw) * (Y - cy)
    x = math.cos(yaw) * (X - cx) - math.sin(yaw) * (Y - cy)
    return C["u0"] + 0.6667 * x / d, C["v0"] + 1.1852 * (cz - Z) / d


def lin_to_srgb(x):
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def patch(a, u, v, w=0.012):
    H, W = a.shape[:2]
    x0, x1 = int((u - w) * W), int((u + w) * W)
    y0, y1 = int((v - w * 16 / 9) * H), int((v + w * 16 / 9) * H)
    return a[max(0, y0):y1, max(0, x0):x1].reshape(-1, a.shape[2])


def L_hsl(rgb01):
    return float(((rgb01.max(1) + rgb01.min(1)) / 2 * 100).mean())


class Toner:
    def __init__(self):
        sc = bpy.context.scene
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.look = "AgX - Medium High Contrast"
        sc.display_settings.display_device = "sRGB"
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGB"
        sc.render.image_settings.color_depth = "8"
        self.sc = sc
        self.tmp = os.path.join(SCRATCH, "r4-tone-tmp.png")

    def load(self, path):
        img = bpy.data.images.load(path, check_existing=False)
        img.colorspace_settings.name = "Linear Rec.709"
        W, H = img.size
        px = np.empty(W * H * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        return img, px.reshape(H, W, 4)[::-1].copy()          # top row first

    def tone(self, img, lin, exposure, gains=None):
        """lin: H x W x 4 linear (top row first). Returns the 8-bit-equivalent sRGB array 0..1 (H x W x 3) after AgX."""
        a = lin.copy()
        if gains is not None:
            a[..., :3] *= np.asarray(gains, dtype=np.float32)
        img.pixels.foreach_set(a[::-1].ravel())
        self.sc.view_settings.exposure = exposure
        img.save_render(self.tmp, scene=self.sc)
        t = bpy.data.images.load(self.tmp, check_existing=False)
        W, H = t.size
        px = np.empty(W * H * 4, dtype=np.float32)
        t.pixels.foreach_get(px)
        bpy.data.images.remove(t)
        return px.reshape(H, W, 4)[::-1, :, :3].copy()


def shoulder(x):
    k, m = SHOULDER_K, SHOULDER_M
    return np.where(x <= k, x, k + (m - k) * np.tanh((x - k) / (m - k)))


def save_png(arr, path):
    from PIL import Image  # noqa: F401  (python with pillow); fall back to bpy below
    Image.fromarray(np.clip(np.rint(arr * 255), 0, 255).astype(np.uint8)).save(path)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="all")
    ap.add_argument("--exr", default=EXR)
    ap.add_argument("--out", default=R4)
    a, _ = ap.parse_known_args(argv)
    plan = json.load(open(os.path.join(a.out, "plan.json")))
    # cameras: masters from house-plan.json, poses from plan.json
    hp = json.load(open(os.path.join(REPO, "docs", "house-plan.json")))
    cams = {c["id"]: dict(loc=c["loc"], yaw=c["yaw_deg_left"], u0=c.get("u0"), v0=c.get("v0")) for c in hp["cameras"] if "lens" in c}
    for pid, p in plan["poses"].items():
        cams[pid] = dict(loc=p["loc"], yaw=p["yaw"], u0=p["u0"], v0=p["v0"])
    rsc = {}
    for g in ("A", "B"):
        pth = os.path.join(a.out, f"selfcheck-render-{g}.json")
        if os.path.exists(pth):
            rsc.update(json.load(open(pth)).get("frames", {}))
    sc_path = os.path.join(a.out, "selfcheck.json")
    out = json.load(open(sc_path)) if os.path.exists(sc_path) else {}
    out.setdefault("frames", {})
    toner = Toner()
    want = None if a.frames == "all" else set(a.frames.split(","))
    for gid, G in GROUPS.items():
        if want is not None and not (want & set(G["frames"])):
            continue
        ref = G["ref"]
        p_ref = os.path.join(a.exr, f"{ref}.exr")
        if not os.path.exists(p_ref):
            print("skip group", gid, "(no EXR for", ref, ")")
            continue
        img, lin = toner.load(p_ref)
        C = cams[ref]
        if isinstance(G["pt"], str):                 # a measured point of the render selfcheck (H0 balance)
            q = rsc[ref]["light_balance"][G["pt"]]
            u, v = q["u"], q["v"]
        elif G["pt"][0] == "uv":
            u, v = G["pt"][1], G["pt"][2]
        else:
            u, v = project(C, *G["pt"][1:])
        if not isinstance(G["pt"], str) and lin.shape[1] == 4072:       # overscan canvas (framing_r4 OS_FRAMES): frame uv -> canvas uv
            u, v = (u * 3840 + 116) / 4072, (v * 2160 + 65) / 2290
        gains = None
        if G.get("wb"):
            # grey world over the mid-tones of the whole reference frame (not the lamp-lit patch alone: that turns the
            # daylit walls blue), then WB_STRENGTH of the correction, luminance kept
            Yl = lin[..., :3] @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
            lo_, hi_ = np.percentile(Yl, 10), np.percentile(Yl, 90)
            sel = lin[..., :3][(Yl > lo_) & (Yl < hi_)]
            m = sel.mean(0)
            g = (m.mean() / m) ** WB_STRENGTH
            g = g / float(g @ np.array([0.2126, 0.7152, 0.0722]))
            gains = tuple(float(x) for x in g)
        # exposure by bisection on the tone-mapped patch L
        lo, hi = -1.0, 4.0
        for _ in range(14):
            e = (lo + hi) / 2
            t = toner.tone(img, lin, e, gains)
            Lp = L_hsl(patch(shoulder(t), u, v))
            if Lp < G["target"]:
                lo = e
            else:
                hi = e
        e_free = round((lo + hi) / 2, 3)
        e = min(max(e_free, EXP_CLAMP[0]), EXP_CLAMP[1]) if G.get("clamp", True) else e_free
        bpy.data.images.remove(img)
        for fid in G["frames"]:
            if want is not None and fid not in want:
                continue
            pe = os.path.join(a.exr, f"{fid}.exr")
            if not os.path.exists(pe):
                print("no EXR", fid)
                continue
            is_pose = fid in plan["poses"]
            img, lin = toner.load(pe)
            raw = toner.tone(img, lin, 1.35)                 # the render exposure, for the before readings
            t = toner.tone(img, lin, e, gains)
            final = shoulder(t)
            bpy.data.images.remove(img)
            dst = os.path.join(a.out, "poses" if is_pose else "", f"{fid}.png")
            save_png(final, dst)
            # readings
            R = dict(group=gid, exposure_group_ref=ref, exposure_unclamped=e_free, exposure_clamp=list(EXP_CLAMP) if G.get("clamp", True) else None, reference_point=G["pt"], reference_uv=[round(u, 4), round(v, 4)],
                     target_L=G["target"], why=G["why"], render_exposure=1.35, exposure=e, exposure_vs_round3_stops=round(e - 0.35, 3),
                     wb_gains=None if gains is None else [round(x, 4) for x in gains],
                     shoulder=f"tanh above {SHOULDER_K} to {SHOULDER_M} per channel", image=os.path.relpath(dst, HERE), pose=is_pose,
                     camera=cams[fid])
            Cf = cams[fid]
            if fid == ref:
                R["reference_L_final"] = round(L_hsl(patch(final, u, v)), 1)
                R["reference_L_render_exposure"] = round(L_hsl(patch(raw, u, v)), 1)
            # wall patches of the render selfcheck, before (render exposure) / after
            wp = {}
            for k, q in (rsc.get(fid, {}).get("wall_patches") or {}).items():
                if isinstance(q, dict) and "u" in q and "L_hsl" in q:
                    lf = round(L_hsl(patch(final, q["u"], q["v"])), 1)
                    wp[k] = dict(u=q["u"], v=q["v"], xyz=q.get("xyz"), L_render=round(L_hsl(patch(raw, q["u"], q["v"])), 1), L_final=lf, L_hsl=lf)
            if 0.02 < u < 0.98 and 0.02 < v < 0.98:
                lf = round(L_hsl(patch(final, u, v)), 1)
                wp[f"reference_{gid}"] = dict(u=round(u, 4), v=round(v, 4), xyz=list(G["pt"][1:]) if isinstance(G["pt"], tuple) else G["pt"],
                                              L_render=round(L_hsl(patch(raw, u, v)), 1), L_final=lf, L_hsl=lf, target=G["target"])
            R["wall_patches"] = wp
            Lmap = (final.max(2) + final.min(2)) / 2 * 100
            R["p99_L_frame"] = round(float(np.percentile(Lmap, 99)), 1)
            R["max_L_frame"] = round(float(Lmap.max()), 1)
            wins = {}
            for k, b in (rsc.get(fid, {}).get("boxes") or {}).items():
                if k.lower().startswith("window") or "glass" in k.lower():
                    H, W = Lmap.shape
                    bb = b["box"]
                    sub = Lmap[int(bb[2] * H):int(bb[3] * H), int(bb[0] * W):int(bb[1] * W)]
                    if sub.size > 100:
                        wins[k] = dict(p99=round(float(np.percentile(sub, 99)), 1), mean=round(float(sub.mean()), 1))
            R["window_p99"] = wins
            R["glass_rolloff_pass"] = bool(all(w["p99"] <= 97 for w in wins.values()) and R["p99_L_frame"] <= 97.5)
            R["mean_L_hsl"] = round(float(Lmap.mean()), 1)
            if fid in ("H0", "C0"):
                lb = rsc.get(fid, {}).get("light_balance", {})
                bal = {}
                for k, q in lb.items():
                    if isinstance(q, dict) and "u" in q and "Y_lin" in q:
                        pp = patch(final, q["u"], q["v"])
                        lin_p = np.where(pp <= 0.04045, pp / 12.92, ((pp + 0.055) / 1.055) ** 2.4)
                        bal[k] = dict(u=q["u"], v=q["v"], L_final=round(L_hsl(pp), 1),
                                      Y_display=round(float((lin_p @ np.array([0.2126, 0.7152, 0.0722])).mean()), 4))
                if fid == "H0" and "living_back_wall_through_door" in bal and "hall_front_wall_above_console" in bal:
                    a_, b_ = bal["living_back_wall_through_door"]["Y_display"], bal["hall_front_wall_above_console"]["Y_display"]
                    bal["living_minus_hall_stops_display"] = round(math.log2(a_ / b_), 2)
                    bal["pass_2_3_stop"] = bool(0.5 <= bal["living_minus_hall_stops_display"] <= 0.9)
                R["light_balance_final"] = bal
            out["frames"][fid] = {**{k: v for k, v in rsc.get(fid, {}).items() if k not in ("wall_patches", "image")}, "image": R["image"],
                                  "wall_patches_render": rsc.get(fid, {}).get("wall_patches"), "wall_patches": wp, "post": R}
            print(fid, "exp", e, "ref L", R.get("reference_L_final"), "p99", R["p99_L_frame"], "win", {k: v["p99"] for k, v in wins.items()}, flush=True)
            json.dump(out, open(sc_path, "w"), indent=1, ensure_ascii=False)
    out.update(stage="round 4 clays (v7 + transition poses), 2026-11-02", tone="tone_r4.py: WB (bath) -> exposure per group -> AgX MHC -> tanh shoulder",
               groups={k: {kk: vv for kk, vv in v.items()} for k, v in GROUPS.items()})
    json.dump(out, open(sc_path, "w"), indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1:])
