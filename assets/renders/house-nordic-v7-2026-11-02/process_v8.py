#!/usr/bin/env python3
"""
process_v8.py: the successor of process_v7.py for the v7 stills (render-agent, 2026-11-03), after the designer's review
(docs/render-v7-review-2026-11-02.md) and QA's gate G1 (qa/reports/2026-11-02-v7-g1.md sections 4 and 5). process_v7.py is
untouched; both old behaviours stay here under flags.

What changed (defaults), and the flag that restores v7:
  --grade-order v2   QA section 4: the v7 chain was roll-off (asymptote L 97.25) -> S curve -> black point, and the last two
                     lift the capped highlights again (0.9725 -> 0.9755 by the S curve, -> 0.978 by the black-point blend),
                     so the window p99 landed at 97.4-97.6 in 7 stills against the 97 ceiling. v2 order: white balance ->
                     exposure (cap +-0.2 stop, unchanged: V7Q4 is open) -> chroma -10 % -> S curve 0.12 -> black point ->
                     roll-off LAST (knee L 94, asymptote L 97.0, max channel, hue kept). The roll-off is then the ceiling:
                     L <= 97.0 everywhere by construction.             (--grade-order v1 = the v7 chain)
  --wb-point auto    QA section 4, B2: process_v7 sampled white balance and exposure at `hero_wall_mid` and fell back to
                     (0.5, 0.3) when a still had none; in B2 that is the mirror, so B2's "-0.12 stop, within cap" was not a
                     wall reading. auto: hero_wall_mid -> else the clay's `reference_*` patch (the group reference wall the
                     clay was exposed on; a pose gets it only when its own clay reads a wall there) -> else (0.5, 0.3), flagged
                     NOT VALID. M0 keeps the Bible corner point.            (--wb-point legacy = the v7 rule)
  --lock v2          lock_v2.py (register + bands + ECC tiles + fixed edges, gate G1.4) instead of the phase-correlation
                     `clay_lock`; the v7 numbers are still written for comparison (`clay_lock_v1`).   (--lock v1)
  --suffix -v2       every output gets the suffix: <id>-graded-v2.png, -frame-v2.png, -graded-os6-v2.png, -measurements-v2.json,
                     -lock-v2.json. Nothing of v7 is overwritten.

Inputs are the normalised 16:9 stills process_v7 already wrote (<out_dir>/<id>.png, 2736x1539 canvas), so step (1)-(2) of
process_v7 (raw copy, non-uniform resize) are not repeated.

  python3 process_v8.py <id> [--render <png>] [--suffix -v2] [--grade-order v1|v2] [--wb-point auto|legacy] [--lock v1|v2]
                        [--out-dir <dir>] [--label <text>]
"""
import argparse
import colorsys
import json
import os
import sys

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import v7_frames as VF  # noqa: E402
import lock_v2 as LK  # noqa: E402

# per-frame grade targets, unchanged from process_v7 (Bible: M0 corner 92-95; hall / corridor 2/3 stop under the living;
# lamp-lit bath 84-88; the rest 90, the agent's working value: G1.8 / BIB1 open)
TARGET_L = {"M0": 93.0, "H0": 82.0, "C0": 82.0, "B1": 86.0, "B2": 86.0}
POSE_BASE = {"H0x": "H0", "H0e": "H0", "M0p": "M0", "M0x": "M0", "PD-35": "D1", "W0-in": "W0", "S1prime": "C0", "R2m": "C0",
             "K-boy-0": "K-boy", "K-girl-0": "K-girl", "CB-0": "B1", "MB-in": "MB0"}
M0_PTS = {"back wall near corner (0.467,0.385) [target 92-95]": (0.467, 0.385), "back wall behind sofa (0.69,0.22) [88-91]": (0.69, 0.22),
          "back wall right edge (0.97,0.31) [82-86]": (0.97, 0.31), "window wall (0.10,0.30)": (0.10, 0.30), "ceiling (0.55,0.04)": (0.55, 0.04),
          "sofa back (0.70,0.60)": (0.70, 0.60), "armchair seat (0.31,0.75)": (0.31, 0.75), "table top oak (0.62,0.715)": (0.62, 0.715)}
M0_WIN = (0.19, 0.375, 0.025, 0.553)
Y = np.array([0.2126, 0.7152, 0.0722])


def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def l2s(x):
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)


def hsl_of(rgb):
    h, l, s = colorsys.rgb_to_hls(*[float(x) for x in rgb])
    return (round(h * 360, 1), round(s * 100, 1), round(l * 100, 1))


def Lmap(arr):
    return (arr.max(2) + arr.min(2)) / 2 * 100


class Still:
    def __init__(self, arr):
        self.a = arr
        self.H, self.W = arr.shape[:2]

    def patch(self, arr, u, v, w=0.01):
        hw = max(2, int(w * self.W / 2))
        x, y = int(u * self.W), int(v * self.H)
        return arr[max(0, y - hw):y + hw + 1, max(0, x - hw):x + hw + 1].reshape(-1, 3).mean(0)


# ---------------------------------------------------------------------------------------------------------------
# sample points
# ---------------------------------------------------------------------------------------------------------------
def choose_points(frame, kind, sc_frame, sc_all, mode):
    """(pts for the readings, white-balance / exposure point, its source, window box, warning)."""
    pts = {}
    for k, v in sc_frame.get("wall_patches", {}).items():
        if "L_hsl" in v:
            pts[f"{k} ({v['u']:.3f},{v['v']:.3f}) clay L {v['L_hsl']}"] = (v["u"], v["v"])
    warn = None
    wp = sc_frame.get("wall_patches", {})
    hero = wp.get("hero_wall_mid", {})
    if "L_hsl" in hero:
        wb_pt, src = (hero["u"], hero["v"]), "hero_wall_mid (clay selfcheck)"
    elif mode == "legacy":
        wb_pt, src = (0.5, 0.3), "default (0.5, 0.3): process_v7 fallback"
        warn = "legacy fallback point: not checked against a wall"
    else:
        refs = {k: v for k, v in wp.items() if k.startswith("reference_") and "L_hsl" in v}
        wb_pt, src = None, None
        if refs:
            k, v = next(iter(refs.items()))
            ok = True
            if kind == "pose":
                base = POSE_BASE.get(frame)
                bl = sc_all.get(base, {}).get("wall_patches", {}).get(k, {}).get("L_hsl")
                ok = bl is not None and abs(v["L_hsl"] - bl) <= 6.0 and 65 <= v["L_hsl"] <= 96
            if ok:
                wb_pt, src = (v["u"], v["v"]), f"{k} (clay reference patch, clay L {v['L_hsl']}, target {v.get('target')})"
        if wb_pt is None:
            wb_pt, src = (0.5, 0.3), "default (0.5, 0.3): no wall patch in the clay selfcheck"
            warn = "NOT VALID: no clay wall patch for this still; the exposure reading is not a wall reading"
    win_box = None
    for nm, b in sc_frame.get("boxes", {}).items():
        if b["kind"] == "window":
            win_box = tuple(b["box"])
    if frame == "H0":
        win_box = (0.26, 0.44, 0.05, 0.95)
    if frame == "M0":
        pts.update(M0_PTS)
        wb_pt, src = (0.467, 0.385), "Bible corner point (0.467, 0.385)"
        win_box = M0_WIN
    if win_box is None:
        win_box = (0.0, 1.0, 0.0, 1.0)
    return pts, wb_pt, src, win_box, warn


# ---------------------------------------------------------------------------------------------------------------
# readings
# ---------------------------------------------------------------------------------------------------------------
def measure(st, arr, pts, win_box, frame):
    W, H = st.W, st.H
    out = {k: hsl_of(st.patch(arr, *p)) for k, p in pts.items()}
    L = Lmap(arr)
    wx0, wx1, wy0, wy1 = int(win_box[0] * W), int(win_box[1] * W), int(win_box[2] * H), int(win_box[3] * H)
    wl = L[wy0:wy1, wx0:wx1]
    sat = arr.max(2) >= 254.5 / 255
    out["brightest area (window / door): L p50 / p99 / max"] = (round(float(np.median(wl)), 1), round(float(np.percentile(wl, 99)), 1), round(float(wl.max()), 1))
    out["pixels with a 255 channel: inside / outside that area"] = (int(sat[wy0:wy1, wx0:wx1].sum()), int(sat.sum() - sat[wy0:wy1, wx0:wx1].sum()))
    out["frame L p99 / max"] = (round(float(np.percentile(L, 99)), 1), round(float(L.max()), 1))
    k = max(4, int(0.005 * W))
    pm = sliding_window_view(L, (k, k))[::4, ::4].mean((2, 3))
    out["darkest 0.5% patch L [12-15]"] = round(float(pm.min()), 1)
    out["frame mean L"] = round(float(L.mean()), 1)
    if frame == "M0":
        reg = arr[int(0.87 * H):int(0.99 * H), int(0.42 * W):int(0.98 * W)].reshape(-1, 3)[::29]
        hls = np.array([colorsys.rgb_to_hls(*c) for c in reg])
        out["floor median HSL (u0.42-0.98,v0.87-0.99) [H30-40 S30-45 L68-78]"] = (round(float(np.median(hls[:, 0])) * 360, 1), round(float(np.median(hls[:, 2])) * 100, 1), round(float(np.median(hls[:, 1])) * 100, 1))
        Lm = np.asarray(Image.fromarray(L.astype(np.float32)).filter(ImageFilter.MedianFilter(3)))
        r = Lm[int(0.76 * H):int(0.83 * H), int(0.52 * W):int(0.84 * W)]
        out["contact shadow under sofa: min L / p1"] = (round(float(r.min()), 1), round(float(np.percentile(r, 1)), 1))
    return out


# ---------------------------------------------------------------------------------------------------------------
# the grade (recipe 2.6), v1 and v2 orders
# ---------------------------------------------------------------------------------------------------------------
def rolloff(lin, knee_L=0.94, asym_L=0.97):
    k_knee = float(s2l(np.array(knee_L)))
    cap = float(s2l(np.array(asym_L)))
    m = lin.max(2, keepdims=True)
    mc = np.where(m > k_knee, k_knee + (cap - k_knee) * (1 - np.exp(-(m - k_knee) / (cap - k_knee))), m)
    return lin * np.where(m > 0, mc / np.maximum(m, 1e-6), 1)


def s_curve(sr, mix=0.12):
    return (1 - mix) * sr + mix * (sr * sr * (3 - 2 * sr))


def black_point(sr, W):
    Lg = Lmap(sr)
    kk = max(4, int(0.005 * W))
    dmin = float(sliding_window_view(Lg, (kk, kk))[::4, ::4].mean((2, 3)).min())
    if dmin < 12.0:
        bp = (0.125 - dmin / 100) / (1 - dmin / 100)
        return bp + (1 - bp) * sr, {"darkest_patch_L_before": round(dmin, 1), "lift_to_L": 12.5, "blend": round(float(bp), 4)}
    return sr, {"darkest_patch_L_before": round(dmin, 1), "lift": "none (already >= 12)"}


def grade(st, wb_pt, target_L, order="v2"):
    a = st.a
    lin = s2l(a)
    g = {"order": order}
    cur = st.patch(a, *wb_pt)
    h, l, s = colorsys.rgb_to_hls(*cur)
    tgt = np.array(colorsys.hls_to_rgb(36 / 360, l, s))
    cur_l, tgt_l = s2l(cur), s2l(tgt)
    gain = (tgt_l / tgt_l.dot(Y)) / (cur_l / cur_l.dot(Y))
    gain = np.clip(gain, 0.9, 1.1)
    g["white_balance"] = {"patch": list(wb_pt), "H_before": round(h * 360, 1), "H_target": 36, "gains_rgb": [round(float(x), 4) for x in gain], "gain_clip": "0.9-1.1"}
    lin = lin * gain
    pl = s2l(st.patch(l2s(lin), *wb_pt)).dot(Y)
    tl = s2l(np.array([target_L / 100] * 3)).dot(Y)
    need = float(np.log2(tl / max(pl, 1e-6)))
    stops = float(np.clip(need, -0.2, 0.2))
    g["exposure"] = {"patch": list(wb_pt), "target_L": target_L, "needed_stops": round(need, 3), "applied_stops": round(stops, 3),
                     "flag": ("DARK: needs more than +0.2 stop, not lifted further" if need > 0.2 else ("bright: needs more than -0.2 stop" if need < -0.2 else "within cap")),
                     "cap": "+-0.2 stop (recipe 2.6.2; V7Q4 open)"}
    lin = lin * 2 ** stops
    lum = (lin * Y).sum(2, keepdims=True)
    lin = lum + 0.90 * (lin - lum)
    g["saturation"] = "chroma x0.90 (linear, toward luminance)"
    if order == "v1":
        lin = rolloff(lin, 0.94, 0.9725)
        g["highlight_rolloff"] = {"knee_L": 94, "asymptote_L": 97.25, "on": "max channel, hue kept", "position": "before the S curve and the black point (v7)"}
        sr = np.clip(l2s(lin), 0, 1)
        sr = s_curve(sr, 0.12)
        g["s_curve"] = {"mix": 0.12, "shape": "smoothstep blend"}
        sr, g["black_point"] = black_point(sr, st.W)
    else:
        sr = np.clip(l2s(lin), 0, 1)
        sr = s_curve(sr, 0.12)
        g["s_curve"] = {"mix": 0.12, "shape": "smoothstep blend"}
        sr, g["black_point"] = black_point(sr, st.W)
        lin2 = rolloff(s2l(np.clip(sr, 0, 1)), 0.94, 0.97)
        sr = np.clip(l2s(lin2), 0, 1)
        g["highlight_rolloff"] = {"knee_L": 94, "asymptote_L": 97.0, "on": "max channel, hue kept", "position": "last (v2): the ceiling of the chain"}
    g["grain"] = "none"
    g["vignette"] = "none"
    return np.clip(sr, 0, 1), g


# ---------------------------------------------------------------------------------------------------------------
def process(fid, render_path=None, suffix="-v2", grade_order="v2", wb_mode="auto", lock_mode="v2", out_dir=None, label=None):
    frame, kind, clay_file, pan, overscan, room = VF.FRAMES[fid]
    od = out_dir or VF.out_dir(fid)
    render_path = render_path or os.path.join(od, fid + ".png")
    sc_all = VF.selfcheck()
    sc = sc_all[frame]
    im = Image.open(render_path).convert("RGB")
    a = np.asarray(im, float) / 255.0
    st = Still(a)
    target_L = TARGET_L.get(POSE_BASE.get(frame, frame), 90.0)
    pts, wb_pt, wb_src, win_box, warn = choose_points(frame, kind, sc, sc_all, wb_mode)
    before = measure(st, a, pts, win_box, frame)
    graded, g = grade(st, wb_pt, target_L, grade_order)
    g["white_balance"]["source"] = wb_src
    g["exposure"]["source"] = wb_src
    if warn:
        g["exposure"]["flag"] += " | " + warn
    gim = Image.fromarray((graded * 255 + 0.5).astype(np.uint8))
    base = os.path.join(od, fid)
    gim.save(base + "-graded" + suffix + ".png")
    after = measure(st, graded, pts, win_box, frame)
    files = {"graded": os.path.relpath(base + "-graded" + suffix + ".png", VF.REPO)}
    if overscan:
        x0, y0, x1, y1 = VF.frame_box_px(st.W, st.H)
        gim.crop((x0, y0, x1, y1)).save(base + "-frame" + suffix + ".png")
        gim.crop((x0, 0, x1, st.H)).save(base + "-graded-os6" + suffix + ".png")
        files["frame"] = os.path.relpath(base + "-frame" + suffix + ".png", VF.REPO)
        files["os6"] = os.path.relpath(base + "-graded-os6" + suffix + ".png", VF.REPO)
    # lock
    lock = None
    if lock_mode == "v2":
        lock = LK.run_frame(fid, render_path=render_path, out_path=base + "-lock" + suffix + ".json")
        files["lock"] = os.path.relpath(base + "-lock" + suffix + ".json", VF.REPO)
    old = {}
    mp = base + "-measurements.json"
    if os.path.exists(mp):
        m = json.load(open(mp))
        old = {"clay_lock_v1_worst_abs_shift_strong_peaks": m.get("clay_lock_worst_abs_shift_strong_peaks"),
               "grade_v1_exposure": m.get("grade", {}).get("exposure"), "measure_after_v1_window": m.get("measure_after", {}).get("brightest area (window / door): L p50 / p99 / max")}
    win_after = after["brightest area (window / door): L p50 / p99 / max"]
    checks = {"window_p99_le_97": bool(win_after[1] <= 97.0), "frame_L_max_le_97": bool(after["frame L p99 / max"][1] <= 97.0 + 1e-6),
              "no_255": bool(sum(after["pixels with a 255 channel: inside / outside that area"]) == 0),
              "black_point_12_15": bool(12.0 <= after["darkest 0.5% patch L [12-15]"] <= 15.0),
              "exposure_within_cap": bool(abs(g["exposure"]["needed_stops"]) <= 0.2), "exposure_point_valid": warn is None}
    res = {"asset_id": fid, "frame": frame, "kind": kind, "label": label, "date": "2026-11-03", "script": "assets/renders/house-nordic-v7-2026-11-02/process_v8.py",
           "settings": {"grade_order": grade_order, "wb_point": wb_mode, "lock": lock_mode, "suffix": suffix},
           "input": os.path.relpath(render_path, VF.REPO), "size_px": [st.W, st.H], "overscan": overscan, "outputs": files,
           "clay": os.path.relpath(os.path.join(VF.R4, clay_file), VF.REPO), "grade_target_L": target_L,
           "sample_point": {"uv": list(wb_pt), "source": wb_src, "warning": warn},
           "measure_before": before, "grade": g, "measure_after": after, "checks": checks, "v7_for_comparison": old,
           "lock_v2_summary": lock["summary"] if lock else None, "lock_v2_verdict": lock["verdict"] if lock else None,
           "product_boxes_clay": VF.product_boxes(frame), "product_box_rule": "each product inside its clay box +-15 % of the box size; read visually"}
    json.dump(res, open(base + "-measurements" + suffix + ".json", "w"), indent=1, ensure_ascii=False)
    e = g["exposure"]
    print(f"== {fid:18s} wb/exp point {wb_src[:40]:40s} need {e['needed_stops']:+.3f} -> {e['applied_stops']:+.2f} {e['flag'][:14]} | "
          f"window p99 {old.get('measure_after_v1_window', ['', '', ''])[1] if old else '-'} -> {win_after[1]} max {win_after[2]} | frame max {after['frame L p99 / max'][1]} | "
          f"black {after['darkest 0.5% patch L [12-15]']} | 255 {after['pixels with a 255 channel: inside / outside that area']}")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--render")
    ap.add_argument("--suffix", default="-v2")
    ap.add_argument("--grade-order", default="v2", choices=["v1", "v2"])
    ap.add_argument("--wb-point", default="auto", choices=["auto", "legacy"])
    ap.add_argument("--lock", default="v2", choices=["v1", "v2"])
    ap.add_argument("--out-dir")
    ap.add_argument("--label")
    a = ap.parse_args()
    process(a.id, a.render, a.suffix, a.grade_order, a.wb_point, a.lock, a.out_dir, a.label)
